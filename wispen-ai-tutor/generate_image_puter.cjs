/**
 * Puter Image Generator via Puppeteer
 * This script launches a headless browser and uses Puter.js to generate images.
 * Usage: node generate_image_puter.cjs "prompt" "output_path.png"
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generateImage(prompt, outputPath) {
    console.log('Launching browser...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        protocolTimeout: 180000 // 3 minutes
    });

    try {
        const page = await browser.newPage();
        page.setDefaultTimeout(120000); // 2 minutes

        // Create minimal HTML that loads Puter.js
        const html = `
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://js.puter.com/v2/"></script>
        </head>
        <body>
            <div id="status">Loading...</div>
            <div id="result"></div>
            <script>
                window.imageReady = false;
                window.imageData = null;
                window.imageError = null;
                
                async function generate(prompt) {
                    try {
                        document.getElementById('status').innerText = 'Generating...';
                        // Use a fast model
                        const img = await puter.ai.txt2img(prompt, { 
                            model: "black-forest-labs/FLUX.1-schnell"
                        });
                        window.imageData = img.src;
                        window.imageReady = true;
                        document.getElementById('status').innerText = 'Done!';
                    } catch (error) {
                        window.imageError = error.message;
                        window.imageReady = true;
                        document.getElementById('status').innerText = 'Error: ' + error.message;
                    }
                }
                
                // Start generation when page loads
                window.startGeneration = function(prompt) {
                    generate(prompt);
                };
            </script>
        </body>
        </html>
        `;

        await page.setContent(html);

        // Wait for Puter.js to load
        console.log('Waiting for Puter to load...');
        await page.waitForFunction(() => typeof puter !== 'undefined' && puter.ai, {
            timeout: 30000
        });

        console.log('Puter loaded, starting generation...');

        // Start the generation (non-blocking)
        await page.evaluate((p) => window.startGeneration(p), prompt);

        // Poll for completion
        console.log('Waiting for image generation...');
        await page.waitForFunction(() => window.imageReady === true, {
            timeout: 120000,
            polling: 1000
        });

        // Get the result
        const result = await page.evaluate(() => {
            if (window.imageError) {
                return { error: window.imageError };
            }
            return { data: window.imageData };
        });

        if (result.error) {
            throw new Error(result.error);
        }

        if (!result.data) {
            throw new Error('No image data returned');
        }

        console.log('Image received, saving...');

        // result.data should be a data URL or image URL
        let imageData;
        if (result.data.startsWith('data:image')) {
            // Base64 data URL
            const base64Data = result.data.replace(/^data:image\/\w+;base64,/, '');
            imageData = Buffer.from(base64Data, 'base64');
        } else if (result.data.startsWith('http')) {
            // Fetch the URL using page context
            const response = await page.goto(result.data, { waitUntil: 'networkidle0' });
            imageData = await response.buffer();
        } else {
            throw new Error('Unknown image format: ' + result.data.substring(0, 100));
        }

        // Ensure output directory exists
        const outputDir = path.dirname(outputPath);
        if (outputDir && !fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }

        fs.writeFileSync(outputPath, imageData);
        console.log('SUCCESS: Image saved to:', outputPath);
        return true;

    } catch (error) {
        console.error('ERROR:', error.message);
        return false;
    } finally {
        await browser.close();
    }
}

// CLI interface
const args = process.argv.slice(2);
if (args.length < 2) {
    console.log('Usage: node generate_image_puter.cjs "prompt" "output_path.png"');
    process.exit(1);
}

const prompt = args[0];
const outputPath = args[1];

generateImage(prompt, outputPath)
    .then(success => process.exit(success ? 0 : 1))
    .catch(err => {
        console.error(err);
        process.exit(1);
    });
