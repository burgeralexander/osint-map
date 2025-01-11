// Simplified Google Search and Image Scraper with Puppeteer
import https from 'https';
import path from 'path';
import fs from 'fs';
import { writeFile } from 'fs/promises';
import puppeteer from 'puppeteer-extra';
import stealthPlugin from 'puppeteer-extra-plugin-stealth';
puppeteer.use(stealthPlugin());

export default class GoogleSearcher {
    constructor() {
        this.browser = null;
        this.page = null;
    }

    async init() {
        this.browser = await puppeteer.launch({
            headless: false,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        this.page = await this.browser.newPage();
    }

    async acceptCookies() {
        try {
            await this.page.waitForSelector('button', { timeout: 5000 });
            const buttons = await this.page.$$('button');
            for (const button of buttons) {
                const text = await this.page.evaluate(el => el.textContent, button);
                if (text.includes('Alle ablehnen')) {
                    await button.click();
                    break;
                }
            }
        } catch (error) {
            console.warn('Cookies button not found or already handled:', error);
        }
    }
    
    async scrollToEnd() {
        try {
            let previousHeight = await this.page.evaluate(() => document.body.scrollHeight);
            while (true) {
                await this.page.evaluate(() => window.scrollBy(0, window.innerHeight));
                await new Promise(resolve => setTimeout(resolve, 1000));
                const newHeight = await this.page.evaluate(() => document.body.scrollHeight);
                if (newHeight === previousHeight) break;
                previousHeight = newHeight;
            }
        } catch (error) {
            console.error('Error during scrolling:', error);
        }
    }
    
    async clickLinkByTextContent(text) {
    try {
        await this.page.evaluate((textContent) => {
            const link = Array.from(document.querySelectorAll('a')).find(a => a.textContent.includes(textContent));
            if (link) {
                link.click();
            }
        }, text);
        await this.page.waitForNavigation();
    } catch (error) {
        console.error(`Error clicking link with text "${text}":`, error);
    }
}


    async searchAndGetLinks(query) {
        let links = [];
        try {
            await this.page.goto(`https://www.google.com/`);
            await this.acceptCookies();
            await this.page.waitForSelector('textarea[name="q"]');

            // Search query
            await this.page.type('textarea[name="q"]', query);
            await this.page.keyboard.press('Enter');
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Scrape links from search results
            while (true) {
                await this.scrollToEnd();
                const newLinks = await this.page.evaluate(() => {
                    return Array.from(document.querySelectorAll('a')).map(link => link.href);
                });
                links.push(...newLinks);

                const nextButton = await this.page.$('a#pnnext');
                if (!nextButton) break;

                await nextButton.click();
                await new Promise(resolve => setTimeout(resolve, 3000));
            }
        } catch (error) {
            console.error('Error during search and link collection:', error);
        }
        return [...new Set(links)]; // Return unique links
    }

    async searchAndGetImageLinks(query) {
        let imageLinks = [];
        try {
            await this.page.goto(`https://www.google.com/`);
            await this.acceptCookies();
            await this.page.waitForSelector('textarea[name="q"]');

            // Search query
            await this.page.type('textarea[name="q"]', query);
            await this.page.keyboard.press('Enter');
            await new Promise(resolve => setTimeout(resolve, 2000));


            // Switch to Images tab
               await this.clickLinkByTextContent('Bilder');
               await new Promise(resolve => setTimeout(resolve, 3000));

                // Scroll and collect image links
                while (true) {
                    const initialCount = imageLinks.length;

                    const newImageLinks = await this.page.evaluate(() => {
                        return Array.from(document.querySelectorAll('img')).map(img => img.src);
                    });
                    imageLinks.push(...newImageLinks);

                    // Ensure unique links
                    imageLinks = [...new Set(imageLinks)];

                    await this.page.evaluate(() => window.scrollBy(0, 10000));
                    await new Promise(resolve => setTimeout(resolve, 3000)); // Adjust delay for images to load

                    const finalCount = imageLinks.length;

                    // Break if no new images are added
                    if (finalCount === initialCount) break;
                }

        } catch (error) {
            console.error('Error during image search and collection:', error);
        }
        return [...new Set(imageLinks)]; // Return unique image links
    }

    async close() {
        if (this.browser) await this.browser.close();
    }

    async scrapeImagesFromUrls(urls) {
        const allImages = new Set();

        for (const url of urls) {
            try {
                console.log(`Navigating to: ${url}`);
                await this.page.goto(url, { waitUntil: 'domcontentloaded' });
                await this.scrollToEnd();

                const images = await this.page.evaluate(() => {
                    return Array.from(document.querySelectorAll('img')).map(img => img.src);
                });

                images.forEach(img => allImages.add(img));
            } catch (error) {
                console.error(`Error scraping images from ${url}:`, error);
            }
        }

        return Array.from(allImages); // Convert Set to Array to return unique images
    }

    async downloadImages(imageUrls, downloadPath) {
    if (!fs.existsSync(downloadPath)) {
        fs.mkdirSync(downloadPath, { recursive: true });
    }

    for (const [index, url] of imageUrls.entries()) {
        try {
            let fileName;

            if (url.startsWith('data:image/')) {
                // Handle base64-encoded images
                const matches = url.match(/^data:(image\/\w+);base64,(.+)$/);
                if (matches) {
                    const extension = matches[1].split('/')[1]; // e.g., 'png', 'jpeg'
                    const base64Data = matches[2];
                    fileName = path.join(downloadPath, `image_${index + 1}.${extension}`);
                    
                    await writeFile(fileName, base64Data, 'base64');
                    console.log(`Saved base64 image to ${fileName}`);
                } else {
                    console.warn(`Skipping invalid base64 URL: ${url}`);
                }
            } else if (url.startsWith('http://') || url.startsWith('https://')) {
                // Handle standard image URLs
                fileName = path.join(downloadPath, `image_${index + 1}.jpg`);
                const file = fs.createWriteStream(fileName);

                await new Promise((resolve, reject) => {
                    https.get(url, (response) => {
                        if (response.statusCode === 200) {
                            response.pipe(file);
                            file.on('finish', () => {
                                file.close();
                                console.log(`Downloaded image from ${url} to ${fileName}`);
                                resolve();
                            });
                        } else {
                            console.error(`Failed to download image from ${url}: HTTP ${response.statusCode}`);
                            file.close();
                            fs.unlink(fileName, () => {}); // Delete incomplete file
                            reject(new Error(`HTTP error ${response.statusCode}`));
                        }
                    }).on('error', (err) => {
                        console.error(`Error downloading image from ${url}:`, err.message);
                        fs.unlink(fileName, () => {}); // Delete incomplete file
                        reject(err);
                    });
                });
            } else {
                console.warn(`Skipping unsupported URL: ${url}`);
            }
        } catch (error) {
            console.error(`Error processing URL: ${url}`, error.message);
        }
    }
    }
}

// Example usage
(async () => {
    const searcher = new GoogleSearcher();
    await searcher.init();

    const query = 'ukraine russland';
    console.log('Fetching links...');
    //const links = await searcher.searchAndGetLinks(query);
    //console.log('Links:', links.length);

    console.log('Fetching image links...');
    const imageLinks = await searcher.searchAndGetImageLinks(query);
    console.log('Image Links:', imageLinks);

    console.log('Scraping images from URLs...');
    //const allImages = await searcher.scrapeImagesFromUrls(links);
    //console.log('Scraped Images:', allImages);
    
    const downloadPath = './downloads';
    console.log('Downloading images...');
    await searcher.downloadImages(imageLinks, downloadPath);
    
    await searcher.close();
})();

